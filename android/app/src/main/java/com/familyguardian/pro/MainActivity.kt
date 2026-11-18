package com.familyguardian.pro

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.BatteryManager
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.zxing.integration.android.IntentIntegrator
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private val prefs by lazy { getSharedPreferences("guardian", MODE_PRIVATE) }
    private val io = Executors.newSingleThreadExecutor()
    private lateinit var server: EditText; private lateinit var code: EditText; private lateinit var status: TextView
    private val permissions = arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContentView(R.layout.activity_main)
        server=findViewById(R.id.server); code=findViewById(R.id.paircode); status=findViewById(R.id.status)
        server.setText(prefs.getString("server", "")); refresh()
        findViewById<TextView>(R.id.battery).text="Battery: ${getSystemService(BATTERY_SERVICE).let { (it as BatteryManager).getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) }}%"
        findViewById<Button>(R.id.scan).setOnClickListener { IntentIntegrator(this).setPrompt("Scan the parent dashboard pairing QR").setOrientationLocked(false).initiateScan() }
        findViewById<Button>(R.id.pair).setOnClickListener { pair() }
        findViewById<Button>(R.id.start).setOnClickListener { if (prefs.getString("token",null)==null) { toast("Pair this device first"); return@setOnClickListener }; if (permissions.any { ContextCompat.checkSelfPermission(this,it)!=PackageManager.PERMISSION_GRANTED }) ActivityCompat.requestPermissions(this,permissions,42) else startSharing() }
        findViewById<Button>(R.id.stop).setOnClickListener { stopService(Intent(this,LocationShareService::class.java)); status.text="Paired · Location sharing is off" }
    }
    override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?) { val r=IntentIntegrator.parseActivityResult(requestCode,resultCode,data); if(r!=null) { if(r.contents!=null) code.setText(r.contents); else toast("QR scan cancelled") } else super.onActivityResult(requestCode,resultCode,data) }
    override fun onRequestPermissionsResult(requestCode:Int,permissions:Array<out String>,grantResults:IntArray){ super.onRequestPermissionsResult(requestCode,permissions,grantResults); if(requestCode==42 && grantResults.any{it==PackageManager.PERMISSION_GRANTED}) startSharing() else if(requestCode==42) toast("Location permission is needed to share location") }
    private fun pair(){ val base=server.text.toString().trim().trimEnd('/'); val pairing=code.text.toString().trim(); if(!base.startsWith("https://") && !base.startsWith("http://10.")){toast("Enter your server URL (use HTTPS outside a private test network)");return}; if(pairing.isBlank()){toast("Enter or scan a pairing code");return}; prefs.edit().putString("server",base).apply(); io.execute { try { val c=URL("$base/api/devices/register").openConnection() as HttpURLConnection; c.requestMethod="POST"; c.connectTimeout=10000;c.readTimeout=10000;c.doOutput=true;c.setRequestProperty("Content-Type","application/json"); c.outputStream.use{it.write(JSONObject().put("pairing_code",pairing).put("name",android.os.Build.MODEL).toString().toByteArray())}; val body=(if(c.responseCode in 200..299)c.inputStream else c.errorStream).bufferedReader().readText(); if(c.responseCode !in 200..299) throw Exception(JSONObject(body).optString("error","Pairing failed")); val j=JSONObject(body); prefs.edit().putString("token",j.getString("device_token")).putString("device_id",j.getString("device_id")).apply();runOnUiThread{refresh();toast("Device paired securely")}}catch(e:Exception){runOnUiThread{toast("Pairing failed: ${e.message}")}} } }
    private fun startSharing(){ ContextCompat.startForegroundService(this,Intent(this,LocationShareService::class.java)); status.text="Paired · Location sharing is active" }
    private fun refresh(){ status.text=if(prefs.getString("token",null)!=null) "Paired · Location sharing is off" else "Not paired · Location sharing is off"; findViewById<TextView>(R.id.device).text="Device: ${prefs.getString("device_id","not paired")}" }
    private fun toast(s:String){Toast.makeText(this,s,Toast.LENGTH_LONG).show()}
}

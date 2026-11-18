package com.familyguardian.pro

import android.app.*
import android.content.Context
import android.content.Intent
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.*
import androidx.core.app.NotificationCompat
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

class LocationShareService: Service(), LocationListener {
    private val io=Executors.newSingleThreadExecutor(); private lateinit var lm:LocationManager
    override fun onBind(intent:Intent?)=null
    override fun onCreate(){super.onCreate(); val channel="location_sharing"; if(Build.VERSION.SDK_INT>=26){getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(channel,"Location sharing",NotificationManager.IMPORTANCE_LOW))}; val stop=PendingIntent.getService(this,1,Intent(this,StopShareService::class.java),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE); val n=NotificationCompat.Builder(this,channel).setSmallIcon(android.R.drawable.ic_menu_mylocation).setContentTitle("Family Guardian · Sharing active").setContentText("Your location is being shared with your family").setOngoing(true).addAction(0,"Stop sharing",stop).build(); startForeground(7,n); lm=getSystemService(Context.LOCATION_SERVICE) as LocationManager; try{lm.requestLocationUpdates(LocationManager.GPS_PROVIDER,60000,25f,this);lm.requestLocationUpdates(LocationManager.NETWORK_PROVIDER,60000,25f,this)}catch(e:SecurityException){stopSelf()} }
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int)=START_STICKY
    override fun onLocationChanged(location:Location){val p=getSharedPreferences("guardian",MODE_PRIVATE);io.execute{try{val c=URL("${p.getString("server","")}/api/locations").openConnection() as HttpURLConnection;c.requestMethod="POST";c.connectTimeout=10000;c.readTimeout=10000;c.doOutput=true;c.setRequestProperty("Authorization","Bearer ${p.getString("token","")}");c.setRequestProperty("Content-Type","application/json");val b=JSONObject().put("latitude",location.latitude).put("longitude",location.longitude).put("accuracy",location.accuracy).put("battery",(getSystemService(BATTERY_SERVICE) as BatteryManager).getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY));c.outputStream.use{it.write(b.toString().toByteArray())};c.inputStream.close();c.disconnect()}catch(_:Exception){} }
    override fun onDestroy(){try{lm.removeUpdates(this)}catch(_:Exception){};super.onDestroy()}
}
class StopShareService: android.app.IntentService("stop-share") { override fun onHandleIntent(intent:Intent?){stopService(Intent(this,LocationShareService::class.java))} }

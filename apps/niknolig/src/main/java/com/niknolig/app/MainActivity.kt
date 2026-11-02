package com.niknolig.app

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Button
import android.widget.Toast

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        findViewById<Button>(R.id.support_contact_button).setOnClickListener {
            startActivity(Intent(this, SupportActivity::class.java))
        }

        findViewById<Button>(R.id.learning_profile_button).setOnClickListener {
            startActivity(Intent(this, LearningProfileActivity::class.java))
        }

        findViewById<Button>(R.id.assistant_button).setOnClickListener {
            startActivity(Intent(this, AssistantActivity::class.java))
        }

        mapOf(
            R.id.tasks_button to TasksActivity::class.java,
            R.id.device_status_button to DeviceStatusActivity::class.java,
            R.id.warnings_button to SecurityActivity::class.java,
        ).forEach { (id, screen) ->
            findViewById<Button>(id).setOnClickListener {
                startActivity(Intent(this, screen))
            }
        }

        findViewById<Button>(R.id.website_button).setOnClickListener {
            try {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(getString(R.string.official_website_url))))
            } catch (_: ActivityNotFoundException) {
                Toast.makeText(this, R.string.support_website_unavailable, Toast.LENGTH_LONG).show()
            } catch (_: SecurityException) {
                Toast.makeText(this, R.string.support_website_unavailable, Toast.LENGTH_LONG).show()
            }
        }
    }
}

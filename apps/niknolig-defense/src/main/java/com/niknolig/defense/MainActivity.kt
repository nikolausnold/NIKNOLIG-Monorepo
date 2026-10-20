package com.niknolig.defense

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button

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
    }
}

package com.signboard.player.player

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import com.signboard.player.model.Marquee

class MarqueeView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {
    
    private var text = ""
    private var speed = 60f  // px/s
    private var fontSize = 28f
    private var fontColor = Color.WHITE
    private var bgColor = Color.BLACK
    
    private var offset = 0f
    private var textWidth = 0f
    
    private val paint = Paint().apply {
        isAntiAlias = true
    }
    
    private var isRunning = false
    
    private val scrollRunnable = object : Runnable {
        override fun run() {
            if (!isRunning) return
            
            offset -= speed / 30f  // 30fps
            if (offset < -textWidth) {
                offset = width.toFloat()
            }
            invalidate()
            postDelayed(this, 33)  // ~30fps
        }
    }
    
    fun configure(marquee: Marquee) {
        this.text = marquee.text
        this.speed = marquee.speed.toFloat()
        this.fontSize = marquee.fontSize.toFloat()
        this.fontColor = Color.parseColor(marquee.fontColor)
        this.bgColor = Color.parseColor(marquee.bgColor)
        
        paint.textSize = this.fontSize
        paint.color = this.fontColor
        textWidth = paint.measureText(text)
        
        post { offset = width.toFloat() }
    }
    
    fun start() {
        isRunning = true
        post(scrollRunnable)
    }
    
    fun stop() {
        isRunning = false
        removeCallbacks(scrollRunnable)
    }
    
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        
        // 绘制背景
        canvas.drawColor(bgColor)
        
        // 绘制文字
        val y = (height + fontSize) / 2 - 4
        canvas.drawText(text, offset, y, paint)
    }
    
    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        start()
    }
    
    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        stop()
    }
}

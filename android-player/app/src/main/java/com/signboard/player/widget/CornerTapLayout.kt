package com.signboard.player.widget

import android.content.Context
import android.util.AttributeSet
import android.view.MotionEvent
import android.widget.FrameLayout

/**
 * 自定义 FrameLayout：拦截四个角落的触摸事件，其他区域正常穿透给子 View
 */
class CornerTapLayout @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : FrameLayout(context, attrs, defStyleAttr) {

    interface OnCornerTapListener {
        fun onCornerTap()
    }

    var cornerTapListener: OnCornerTapListener? = null
    var cornerSizePx: Int = 0

    override fun onInterceptTouchEvent(ev: MotionEvent): Boolean {
        if (ev.action != MotionEvent.ACTION_DOWN) return false

        val x = ev.x.toInt()
        val y = ev.y.toInt()
        val w = width
        val h = height
        val cs = cornerSizePx

        val inCorner = (x < cs && y < cs) ||
            (x > w - cs && y < cs) ||
            (x < cs && y > h - cs) ||
            (x > w - cs && y > h - cs)

        return inCorner // 只拦截角落，其他区域不拦截
    }

    override fun onTouchEvent(ev: MotionEvent): Boolean {
        if (ev.action == MotionEvent.ACTION_UP) {
            cornerTapListener?.onCornerTap()
        }
        return true
    }
}

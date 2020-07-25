package controllers

import (
	"github.com/gin-gonic/gin"
)

func GetRouter() *gin.Engine {
	r := gin.Default()
	r.RedirectTrailingSlash = true

	codeCountCtrl := CodeCountController{}
	r.POST("/github/:org/code/counts", codeCountCtrl.Create)

	return r
}

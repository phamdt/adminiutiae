package controllers

import (
	"github.com/gin-gonic/gin"
	"github.com/jmoiron/sqlx"
)

func GetRouter(db *sqlx.DB) *gin.Engine {
	r := gin.Default()
	r.RedirectTrailingSlash = true

	codeCountCtrl := CodeCountController{db: db}
	r.POST("/github/:org/code/counts", codeCountCtrl.Create)

	return r
}

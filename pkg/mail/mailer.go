package mail

import (
	"crypto/tls"

	gomail "gopkg.in/mail.v2"
)

// Mailer is a wrapper for gomail
type Mailer struct {
	SMTPHost           string
	SMTPPort           int
	Username           string
	Password           string
	fromNoReply        string
	InsecureSkipVerify bool
}

// Send mails the message to the configured SMTP server
func (ma *Mailer) Send(m IMessage) error {
	d := gomail.NewDialer(ma.SMTPHost, ma.SMTPPort, ma.Username, ma.Password)
	d.TLSConfig = &tls.Config{InsecureSkipVerify: ma.InsecureSkipVerify}

	msg := m.(*gomail.Message)
	if err := d.DialAndSend(msg); err != nil {
		return err
	}
	return nil
}

// NewMessage sets the initial base mail message to be built upon
func (ma *Mailer) NewMessage() *Message {
	return &Message{
		m: gomail.NewMessage(),
	}
}

// FromNoReply returns the no reply email
func (ma *Mailer) FromNoReply() string {
	return ma.fromNoReply
}

// SetNoReply is a setter for fromNoReply
func (ma *Mailer) SetNoReply(fromNoReply string) {
	ma.fromNoReply = fromNoReply
}

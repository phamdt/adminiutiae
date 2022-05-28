package mail

import (
	gomail "gopkg.in/mail.v2"
)

const defaultContentType = "text/html"

// IMessage is an interface for mail messages
type IMessage interface {
	SetHeader(string, ...string)
}

// Message abstracts the gomail library's Message and provides a builder
// interface for creating and setting the properties of a message
type Message struct {
	m           *gomail.Message
	contentType string
}

// From builds the from header into the message
func (m *Message) From(from string) *Message {
	m.m.SetHeader("From", from)
	return m
}

// To builds the to header into the message
func (m *Message) To(to []string) *Message {
	m.m.SetHeader("To", to...)
	return m
}

// Bcc builds the bcc header into the message
func (m *Message) Bcc(bcc []string) *Message {
	m.m.SetHeader("Bcc", bcc...)
	return m
}

// Subject builds the subject header into the message
func (m *Message) Subject(s string) *Message {
	m.m.SetHeader("Subject", s)
	return m
}

// Body builds the body into the message
func (m *Message) Body(s string) *Message {
	if m.contentType == "" {
		m.contentType = defaultContentType
	}
	m.m.SetBody(m.contentType, s)
	return m
}

// ContentType builds the content type of the message. This must be called
// before setting the body.
func (m *Message) ContentType(t string) *Message {
	m.contentType = t
	return m
}

// SetHeader sets headers of the underlying message
func (m *Message) SetHeader(header string, values ...string) {
	m.m.SetHeader(header, values...)
}

// Build returns underlying message construct
func (m *Message) Build() *gomail.Message {
	return m.m
}

// GetHeader is mostly for debugging
func (m *Message) GetHeader(field string) []string {
	return m.m.GetHeader(field)
}

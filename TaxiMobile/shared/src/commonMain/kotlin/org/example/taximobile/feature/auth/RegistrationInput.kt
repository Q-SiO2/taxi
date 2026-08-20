package org.example.taximobile.feature.auth

/**
 * Usability-only registration checks aligned with the public API shape.
 *
 * These checks decide whether the form can be submitted; they never establish
 * identity or replace server validation. Phone canonicalization remains a
 * backend responsibility.
 */
data class RegistrationInputValidity(
    val emailValid: Boolean,
    val phoneNumberValid: Boolean,
    val canSubmit: Boolean,
)

fun registrationInputValidity(
    displayName: String,
    email: String,
    phoneNumber: String,
    password: String,
): RegistrationInputValidity {
    val emailCandidate = email.trim()
    val phoneCandidate = phoneNumber.trim()
    val emailValid = emailCandidate.isBlank() || validEmailShape(emailCandidate)
    val phoneNumberValid = phoneCandidate.isBlank() || validMoroccanPhoneShape(phoneCandidate)
    return RegistrationInputValidity(
        emailValid = emailValid,
        phoneNumberValid = phoneNumberValid,
        canSubmit = displayName.trim().isNotEmpty() &&
            password.length >= 12 &&
            emailValid &&
            phoneNumberValid &&
            (emailCandidate.isNotEmpty() || phoneCandidate.isNotEmpty()),
    )
}

private fun validEmailShape(value: String): Boolean {
    val at = value.indexOf('@')
    return at > 0 && at == value.lastIndexOf('@') && at < value.lastIndex
}

private fun validMoroccanPhoneShape(value: String): Boolean {
    val compact = value.filterNot { it.isWhitespace() || it in "().-" }
    val canonical = when {
        compact.startsWith("00") -> "+${compact.drop(2)}"
        compact.startsWith("0") -> "+212${compact.drop(1)}"
        else -> compact
    }
    return canonical.startsWith("+212") && canonical.length == 13 && canonical.drop(4).all(Char::isDigit)
}

#include "connect_break.h"
#include "../failure_mode_factory.h"
#include "../failure_mode.h"

namespace diag {

static AutoRegister<ConnectBreak> connect("001");

bool ConnectBreak::isValid() {
    return true;
}

std::string ConnectBreak::GetName() const {
    return "001";
}

std::string ConnectBreak::GetRootCauseDesc() const {
    return "见下级组件";
}

RootCause ConnectBreak::AnalyzeRootCause() {
    return RootCause(false, GetRootCauseDesc());
}

std::string ConnectBreak::GetFixSuggDesc() const {
    return "见下级组件";
}

std::string ConnectBreak::GetValidationMethodDesc() const {
    return "查看urma日志";
}

std::string ConnectBreak::GetId() const {
    return "001";
}
}
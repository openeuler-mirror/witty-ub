#include "urma_failure_724.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure724> g_urma("urma_724");

bool UrmaFailure724::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_set_bonding_mode' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Unsupported bonding level:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure724::GetName() const
{
    return "设置设备过程中依赖步骤失败";
}

std::string UrmaFailure724::GetRootCauseDesc() const
{
    return "函数用于设置设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure724::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure724::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure724::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_set_bonding_mode，Unsupported bonding level:";
}

std::string UrmaFailure724::GetId() const
{
    return "urma_724";
}

} // namespace diag

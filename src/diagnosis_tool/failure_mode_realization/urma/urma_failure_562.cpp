#include "urma_failure_562.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure562> g_urma("urma_562");

bool UrmaFailure562::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'schedule_send_balance' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Unsupported bonding level:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure562::GetName() const
{
    return "激活设备过程中依赖步骤失败";
}

std::string UrmaFailure562::GetRootCauseDesc() const
{
    return "函数用于激活设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure562::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure562::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure562::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：schedule_send_balance，Unsupported bonding level:";
}

std::string UrmaFailure562::GetId() const
{
    return "urma_562";
}

} // namespace diag

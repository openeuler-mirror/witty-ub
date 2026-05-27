#include "urma_failure_561.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure561> g_urma("urma_561");

bool UrmaFailure561::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'schedule_send_balance' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid min_active_count.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure561::GetName() const
{
    return "执行URMA资源所需输入对象无效导致激活组件失败";
}

std::string UrmaFailure561::GetRootCauseDesc() const
{
    return "函数用于激活组件，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure561::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure561::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure561::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：schedule_send_balance，Invalid min_active_count.";
}

std::string UrmaFailure561::GetId() const
{
    return "urma_561";
}

} // namespace diag

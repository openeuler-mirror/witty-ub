#include "urma_failure_759.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure759> g_urma("urma_759");

bool UrmaFailure759::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_opt_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'invalid opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure759::GetName() const
{
    return "执行URMA资源所需输入对象无效导致执行JFS失败";
}

std::string UrmaFailure759::GetRootCauseDesc() const
{
    return "函数用于执行JFS，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure759::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure759::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure759::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_opt_valid，invalid opt len";
}

std::string UrmaFailure759::GetId() const
{
    return "urma_759";
}

} // namespace diag

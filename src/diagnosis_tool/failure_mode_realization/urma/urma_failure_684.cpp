#include "urma_failure_684.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure684> g_urma("urma_684");

bool UrmaFailure684::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_net_addr_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure684::GetName() const
{
    return "释放URMA资源所需输入对象无效导致释放URMA资源失败";
}

std::string UrmaFailure684::GetRootCauseDesc() const
{
    return "函数用于释放URMA资源，调用方传入的释放URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure684::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure684::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure684::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_net_addr_list，Invalid parameter.";
}

std::string UrmaFailure684::GetId() const
{
    return "urma_684";
}

} // namespace diag

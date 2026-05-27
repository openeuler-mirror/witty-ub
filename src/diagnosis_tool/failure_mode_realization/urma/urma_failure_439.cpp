#include "urma_failure_439.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure439> g_urma("urma_439");

bool UrmaFailure439::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_net_addr_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure439::GetName() const
{
    return "URMA context无效导致获取ioctl失败";
}

std::string UrmaFailure439::GetRootCauseDesc() const
{
    return "函数用于获取ioctl，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure439::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure439::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure439::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_net_addr_list，Invalid parameter.";
}

std::string UrmaFailure439::GetId() const
{
    return "urma_439";
}

} // namespace diag

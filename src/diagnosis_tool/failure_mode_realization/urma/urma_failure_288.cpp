#include "urma_failure_288.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure288> g_urma("urma_288");

bool UrmaFailure288::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to alloc notifier.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure288::GetName() const
{
    return "Notifier相关临时结构或命令参数分配失败";
}

std::string UrmaFailure288::GetRootCauseDesc() const
{
    return "函数在分配Notifier前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure288::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure288::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure288::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jetty，Failed to alloc notifier.";
}

std::string UrmaFailure288::GetId() const
{
    return "urma_288";
}

} // namespace diag

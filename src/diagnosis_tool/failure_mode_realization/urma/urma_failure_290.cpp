#include "urma_failure_290.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure290> g_urma("urma_290");

bool UrmaFailure290::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to alloc notifier.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure290::GetName() const
{
    return "Notifier相关临时结构或命令参数分配失败";
}

std::string UrmaFailure290::GetRootCauseDesc() const
{
    return "函数在分配Notifier前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure290::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure290::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure290::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jetty，Failed to alloc notifier.。";
}

std::string UrmaFailure290::GetId() const
{
    return "urma_290";
}

} // namespace diag

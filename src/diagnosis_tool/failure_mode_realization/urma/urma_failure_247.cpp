#include "urma_failure_247.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure247> g_urma("urma_247");

bool UrmaFailure247::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unadvise_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to alloc incomplete_tjetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure247::GetName() const
{
    return "Jetty相关临时结构或命令参数分配失败";
}

std::string UrmaFailure247::GetRootCauseDesc() const
{
    return "函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure247::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure247::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure247::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unadvise_jetty，Failed to alloc incomplete_tjetty.。";
}

std::string UrmaFailure247::GetId() const
{
    return "urma_247";
}

} // namespace diag

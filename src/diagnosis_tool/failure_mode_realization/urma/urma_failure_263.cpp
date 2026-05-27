#include "urma_failure_263.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure263> g_urma("urma_263");

bool UrmaFailure263::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'alloc_jetty failed.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure263::GetName() const
{
    return "Jetty相关临时结构或命令参数分配失败";
}

std::string UrmaFailure263::GetRootCauseDesc() const
{
    return "函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure263::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure263::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure263::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jetty，alloc_jetty failed.。";
}

std::string UrmaFailure263::GetId() const
{
    return "urma_263";
}

} // namespace diag

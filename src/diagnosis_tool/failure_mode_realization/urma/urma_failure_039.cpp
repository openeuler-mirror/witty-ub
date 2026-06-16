#include "urma_failure_039.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure039> g_urma("urma_039");

bool UrmaFailure039::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'failed to init alloc jetty cmd'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure039::GetName() const
{
    return "Jetty相关临时结构或命令参数分配失败";
}

std::string UrmaFailure039::GetRootCauseDesc() const
{
    return "函数在初始化Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure039::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure039::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure039::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jetty，failed to init alloc jetty cmd。";
}

std::string UrmaFailure039::GetId() const
{
    return "urma_039";
}

} // namespace diag

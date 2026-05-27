#include "urma_failure_139.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure139> g_urma("urma_139");

bool UrmaFailure139::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jetty_batch' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to malloc buffer.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure139::GetName() const
{
    return "Jetty相关临时结构或命令参数分配失败";
}

std::string UrmaFailure139::GetRootCauseDesc() const
{
    return "函数在删除Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure139::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure139::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure139::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty_batch，Failed to malloc buffer.。";
}

std::string UrmaFailure139::GetId() const
{
    return "urma_139";
}

} // namespace diag

#include "urma_failure_376.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure376> g_urma("urma_376");

bool UrmaFailure376::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfc_batch' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to malloc buffer.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure376::GetName() const
{
    return "JFC相关临时结构或命令参数分配失败";
}

std::string UrmaFailure376::GetRootCauseDesc() const
{
    return "函数在删除JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure376::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure376::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure376::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc_batch，Failed to malloc buffer.。";
}

std::string UrmaFailure376::GetId() const
{
    return "urma_376";
}

} // namespace diag

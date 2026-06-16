#include "urma_failure_399.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure399> g_urma("urma_399");

bool UrmaFailure399::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfr_batch' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to alloc memory.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure399::GetName() const
{
    return "JFR相关临时结构或命令参数分配失败";
}

std::string UrmaFailure399::GetRootCauseDesc() const
{
    return "函数在分配JFR前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure399::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure399::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure399::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr_batch，Failed to alloc memory.。";
}

std::string UrmaFailure399::GetId() const
{
    return "urma_399";
}

} // namespace diag

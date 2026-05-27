#include "urma_failure_833.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure833> g_urma("urma_833");

bool UrmaFailure833::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Local only access is not allowed to config with other accesses.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure833::GetName() const
{
    return "设置Segment过程中依赖步骤失败";
}

std::string UrmaFailure833::GetRootCauseDesc() const
{
    return "函数用于设置Segment，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure833::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure833::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure833::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_seg_cfg，Local only access is not allowed to config with other "
           "accesses.";
}

std::string UrmaFailure833::GetId() const
{
    return "urma_833";
}

} // namespace diag

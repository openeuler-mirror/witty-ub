#include "urma_failure_181.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure181> g_urma("urma_181");

bool UrmaFailure181::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_trans_mode' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'UB dev should use share jfr!'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure181::GetName() const
{
    return "创建设备过程中依赖步骤失败";
}

std::string UrmaFailure181::GetRootCauseDesc() const
{
    return "函数用于创建设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure181::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure181::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure181::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_create_jetty_check_trans_mode，UB dev should use share jfr!";
}

std::string UrmaFailure181::GetId() const
{
    return "urma_181";
}

} // namespace diag

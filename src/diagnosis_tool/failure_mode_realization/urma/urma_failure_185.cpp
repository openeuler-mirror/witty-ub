#include "urma_failure_185.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure185> g_urma("urma_185");

bool UrmaFailure185::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_dev_cap' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty_grp jetty cnt:' | grep -F ', max_jetty in grp:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure185::GetName() const
{
    return "创建Jetty过程中依赖步骤失败";
}

std::string UrmaFailure185::GetRootCauseDesc() const
{
    return "函数用于创建Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure185::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure185::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure185::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_create_jetty_check_dev_cap，jetty_grp jetty cnt:，, max_jetty in grp:";
}

std::string UrmaFailure185::GetId() const
{
    return "urma_185";
}

} // namespace diag

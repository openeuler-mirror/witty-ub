#include "urma_failure_812.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure812> g_urma("urma_812");

bool UrmaFailure812::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'jfr cfg "
        "out of range, depth:' | grep -F ', max_depth:' | grep -F ', sge:' | grep -F ', max_sge:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure812::GetName() const
{
    return "去激活JFR过程中依赖步骤失败";
}

std::string UrmaFailure812::GetRootCauseDesc() const
{
    return "函数用于去激活JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure812::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure812::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure812::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfs，jfr cfg out of range, depth:，, max_depth:，, "
           "sge:，, max_sge:。";
}

std::string UrmaFailure812::GetId() const
{
    return "urma_812";
}

} // namespace diag

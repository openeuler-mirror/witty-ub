#include "urma_failure_772.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure772> g_urma("urma_772");

bool UrmaFailure772::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfc cfg depth of range, depth:' | grep -F ', max_depth:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure772::GetName() const
{
    return "激活JFC过程中依赖步骤失败";
}

std::string UrmaFailure772::GetRootCauseDesc() const
{
    return "函数用于激活JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure772::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure772::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure772::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfc，jfc cfg depth of range, depth:，, max_depth:";
}

std::string UrmaFailure772::GetId() const
{
    return "urma_772";
}

} // namespace diag

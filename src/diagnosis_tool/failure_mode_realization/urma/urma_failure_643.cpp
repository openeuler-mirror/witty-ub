#include "urma_failure_643.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure643> g_urma("urma_643");

bool UrmaFailure643::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfc still actived, please deactived first'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure643::GetName() const
{
    return "释放JFC过程中依赖步骤失败";
}

std::string UrmaFailure643::GetRootCauseDesc() const
{
    return "函数用于释放JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure643::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure643::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure643::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_jfc，jfc still actived, please deactived first";
}

std::string UrmaFailure643::GetId() const
{
    return "urma_643";
}

} // namespace diag

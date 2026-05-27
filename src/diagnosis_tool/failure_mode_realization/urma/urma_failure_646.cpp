#include "urma_failure_646.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure646> g_urma("urma_646");

bool UrmaFailure646::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_free_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'There is "
        "jfc event and it must be acked, jfc_comp:' | grep -F ', comp:' | grep -F ', jfc_async:' | grep -F ', async:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure646::GetName() const
{
    return "释放JFC过程中依赖步骤失败";
}

std::string UrmaFailure646::GetRootCauseDesc() const
{
    return "函数用于释放JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure646::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure646::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure646::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfc，There is jfc event and it must be acked, "
           "jfc_comp:，, comp:，, jfc_async:，, async:。";
}

std::string UrmaFailure646::GetId() const
{
    return "urma_646";
}

} // namespace diag

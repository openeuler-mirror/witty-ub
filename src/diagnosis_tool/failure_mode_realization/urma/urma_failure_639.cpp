#include "urma_failure_639.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure639> g_urma("urma_639");

bool UrmaFailure639::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_free_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'There is jfc event and it must be acked, jfc_comp:' | grep -F ', comp:' | grep -F ', jfc_async:' | "
        "grep -F ', async:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure639::GetName() const
{
    return "释放JFC过程中依赖步骤失败";
}

std::string UrmaFailure639::GetRootCauseDesc() const
{
    return "函数用于释放JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure639::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure639::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure639::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_free_jfc，There is jfc event and it must be acked, jfc_comp:，, "
           "comp:，, jfc_async:，, async:";
}

std::string UrmaFailure639::GetId() const
{
    return "urma_639";
}

} // namespace diag

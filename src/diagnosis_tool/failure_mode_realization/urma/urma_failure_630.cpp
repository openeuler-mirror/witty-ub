#include "urma_failure_630.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure630> g_urma("urma_630");

bool UrmaFailure630::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'There is jfc event and it must be acked, jfc_comp:' | grep -F ', comp:' | grep -F ', jfc_async:' | "
        "grep -F ', async:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure630::GetName() const
{
    return "删除JFC过程中依赖步骤失败";
}

std::string UrmaFailure630::GetRootCauseDesc() const
{
    return "函数用于删除JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure630::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure630::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure630::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfc，There is jfc event and it must be acked, jfc_comp:，, "
           "comp:，, jfc_async:，, async:";
}

std::string UrmaFailure630::GetId() const
{
    return "urma_630";
}

} // namespace diag

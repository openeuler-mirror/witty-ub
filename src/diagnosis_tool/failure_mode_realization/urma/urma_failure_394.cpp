#include "urma_failure_394.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure394> g_urma("urma_394");

bool UrmaFailure394::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfs cfg out of range, depth:' | grep -F ', max_depth:' | grep -F ', inline_data:' | "
        "grep -F ', max_inline_len:' | grep -F ', sge:' | grep -F 'hu, max_sge:' | grep -F ', rsge:' | "
        "grep -F 'hu, max_rsge:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure394::GetName() const
{
    return "分配JFS过程中依赖步骤失败";
}

std::string UrmaFailure394::GetRootCauseDesc() const
{
    return "函数用于分配JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure394::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure394::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure394::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfs，jfs cfg out of range, depth:，, max_depth:，, inline_data:，, "
           "max_inline_len:，, sge:，hu, max_sge:，, rsge:，hu, max_rsge:";
}

std::string UrmaFailure394::GetId() const
{
    return "urma_394";
}

} // namespace diag

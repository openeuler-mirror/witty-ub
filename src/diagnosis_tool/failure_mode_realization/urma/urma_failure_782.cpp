#include "urma_failure_782.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure782> g_urma("urma_782");

bool UrmaFailure782::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_order_type' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfs cfg out of range, depth:' | grep -F ', max_depth:' | grep -F ', inline_data:' | "
        "grep -F ', max_inline_len:' | grep -F ', sge:' | grep -F 'hu, max_sge:' | grep -F ', rsge:' | "
        "grep -F 'hu, max_rsge:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure782::GetName() const
{
    return "创建JFS过程中依赖步骤失败";
}

std::string UrmaFailure782::GetRootCauseDesc() const
{
    return "函数用于创建JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure782::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure782::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure782::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_order_type，jfs cfg out of range, depth:，, max_depth:，, "
           "inline_data:，, max_inline_len:，, sge:，hu, max_sge:，, rsge:，hu, max_rsge:";
}

std::string UrmaFailure782::GetId() const
{
    return "urma_782";
}

} // namespace diag

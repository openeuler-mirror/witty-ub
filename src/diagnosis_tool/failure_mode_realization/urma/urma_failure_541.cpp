#include "urma_failure_541.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure541> g_urma("urma_541");

bool UrmaFailure541::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'token_id "
        "must set when token_id_valid is true, or must NULL when token_id_valid is false.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure541::GetName() const
{
    return "设置Token过程中依赖步骤失败";
}

std::string UrmaFailure541::GetRootCauseDesc() const
{
    return "函数用于设置Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure541::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure541::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure541::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_seg_cfg，token_id must set when token_id_valid is true, or "
           "must NULL when token_id_valid is false.。";
}

std::string UrmaFailure541::GetId() const
{
    return "urma_541";
}

} // namespace diag

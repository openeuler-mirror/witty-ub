#include "urma_failure_519.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure519> g_urma("urma_519");

bool UrmaFailure519::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to lookup v2p_token_id, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure519::GetName() const
{
    return "解除导入Token过程中依赖步骤失败";
}

std::string UrmaFailure519::GetRootCauseDesc() const
{
    return "函数用于解除导入Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次UR"
           "MA操作失败。";
}

RootCause UrmaFailure519::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure519::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure519::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unimport_pseg，Failed to lookup v2p_token_id, ret:";
}

std::string UrmaFailure519::GetId() const
{
    return "urma_519";
}

} // namespace diag

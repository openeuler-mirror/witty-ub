#include "urma_failure_344.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure344> g_urma("urma_344");

bool UrmaFailure344::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vcontext' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to create remote_v2p_token_id_table'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure344::GetName() const
{
    return "Token创建时下层资源准备失败";
}

std::string UrmaFailure344::GetRootCauseDesc() const
{
    return "函数负责创建Token，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure344::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure344::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure344::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vcontext，Failed to create remote_v2p_token_id_table。";
}

std::string UrmaFailure344::GetId() const
{
    return "urma_344";
}

} // namespace diag

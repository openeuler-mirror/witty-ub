#include "urma_failure_349.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure349> g_urma("urma_349");

bool UrmaFailure349::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pcontext' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to create ctx'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure349::GetName() const
{
    return "context创建时下层资源准备失败";
}

std::string UrmaFailure349::GetRootCauseDesc() const
{
    return "函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure349::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure349::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure349::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pcontext，Failed to create ctx。";
}

std::string UrmaFailure349::GetId() const
{
    return "urma_349";
}

} // namespace diag

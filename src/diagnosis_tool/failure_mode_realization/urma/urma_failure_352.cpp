#include "urma_failure_352.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure352> g_urma("urma_352");

bool UrmaFailure352::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pcontext' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to create health check scene'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure352::GetName() const
{
    return "健康检查创建时下层资源准备失败";
}

std::string UrmaFailure352::GetRootCauseDesc() const
{
    return "函数负责创建健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure352::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure352::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure352::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pcontext，Failed to create health check scene。";
}

std::string UrmaFailure352::GetId() const
{
    return "urma_352";
}

} // namespace diag

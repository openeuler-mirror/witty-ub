#include "urma_failure_509.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure509> g_urma("urma_509");

bool UrmaFailure509::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'import_check_tseg_by_import_result' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to import health check seg ('");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure509::GetName() const
{
    return "健康检查导入时下层资源准备失败";
}

std::string UrmaFailure509::GetRootCauseDesc() const
{
    return "函数负责导入健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure509::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure509::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure509::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：import_check_tseg_by_import_result，Failed to import health check seg "
           "(。";
}

std::string UrmaFailure509::GetId() const
{
    return "urma_509";
}

} // namespace diag

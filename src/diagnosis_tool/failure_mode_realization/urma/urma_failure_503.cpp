#include "urma_failure_503.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure503> g_urma("urma_503");

bool UrmaFailure503::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'RM jfr import requires drv_ext.vjfs'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure503::GetName() const
{
    return "JFR导入时下层资源准备失败";
}

std::string UrmaFailure503::GetRootCauseDesc() const
{
    return "函数负责导入JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure503::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure503::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure503::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unimport_pjfr，RM jfr import requires drv_ext.vjfs";
}

std::string UrmaFailure503::GetId() const
{
    return "urma_503";
}

} // namespace diag

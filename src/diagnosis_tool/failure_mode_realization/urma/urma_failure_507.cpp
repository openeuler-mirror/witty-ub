#include "urma_failure_507.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure507> g_urma("urma_507");

bool UrmaFailure507::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_import_pjfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to import tjfr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure507::GetName() const
{
    return "物理 JFR导入时下层资源准备失败";
}

std::string UrmaFailure507::GetRootCauseDesc() const
{
    return "函数负责导入物理 JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure507::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure507::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure507::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_pjfr，Failed to import tjfr。";
}

std::string UrmaFailure507::GetId() const
{
    return "urma_507";
}

} // namespace diag

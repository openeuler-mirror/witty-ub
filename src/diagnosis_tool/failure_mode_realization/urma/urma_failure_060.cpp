#include "urma_failure_060.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure060> g_urma("urma_060");

bool UrmaFailure060::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfr_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create pjfr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure060::GetName() const
{
    return "物理 JFR创建时下层资源准备失败";
}

std::string UrmaFailure060::GetRootCauseDesc() const
{
    return "函数负责创建物理 JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure060::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure060::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure060::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jfr_p_vjetty_info，Failed to create pjfr";
}

std::string UrmaFailure060::GetId() const
{
    return "urma_060";
}

} // namespace diag

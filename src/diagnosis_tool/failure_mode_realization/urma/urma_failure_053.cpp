#include "urma_failure_053.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure053> g_urma("urma_053");

bool UrmaFailure053::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfs_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create bondp comp'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure053::GetName() const
{
    return "组件创建时下层资源准备失败";
}

std::string UrmaFailure053::GetRootCauseDesc() const
{
    return "函数负责创建组件，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure053::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure053::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure053::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jfs_p_vjetty_info，Failed to create bondp comp";
}

std::string UrmaFailure053::GetId() const
{
    return "urma_053";
}

} // namespace diag

#include "urma_failure_054.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure054> g_urma("urma_054");

bool UrmaFailure054::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfs_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create pjfs'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure054::GetName() const
{
    return "物理 JFS创建时下层资源准备失败";
}

std::string UrmaFailure054::GetRootCauseDesc() const
{
    return "函数负责创建物理 JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure054::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure054::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure054::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jfs_p_vjetty_info，Failed to create pjfs";
}

std::string UrmaFailure054::GetId() const
{
    return "urma_054";
}

} // namespace diag

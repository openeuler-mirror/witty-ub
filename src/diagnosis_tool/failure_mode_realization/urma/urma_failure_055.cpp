#include "urma_failure_055.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure055> g_urma("urma_055");

bool UrmaFailure055::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfs_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create vjfs'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure055::GetName() const
{
    return "虚拟 JFS创建时下层资源准备失败";
}

std::string UrmaFailure055::GetRootCauseDesc() const
{
    return "函数负责创建虚拟 JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure055::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure055::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure055::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jfs_p_vjetty_info，Failed to create vjfs";
}

std::string UrmaFailure055::GetId() const
{
    return "urma_055";
}

} // namespace diag

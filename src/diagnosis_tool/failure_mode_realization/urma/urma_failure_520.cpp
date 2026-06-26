#include "urma_failure_520.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure520> g_urma("urma_520");

bool UrmaFailure520::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_set_bonding_mode") != std::string::npos &&
           message.find("Failed to delete pctx when set bonding mode, ret:") != std::string::npos;
}

std::string UrmaFailure520::GetName() const
{
    return "下层资源删除失败导致设置bonding、MODE失败";
}

std::string UrmaFailure520::GetRootCauseDesc() const
{
    return "bondp_set_bonding_"
           "mode清理bonding、MODE时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure520::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure520::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure520::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_set_bonding_mode，Failed to delete pctx when set bonding mode, "
           "ret:。";
}

std::string UrmaFailure520::GetId() const
{
    return "urma_520";
}
} // namespace diag

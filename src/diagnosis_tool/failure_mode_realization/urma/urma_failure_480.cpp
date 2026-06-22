#include "urma_failure_480.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure480> g_urma("urma_480");

bool UrmaFailure480::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfce") != std::string::npos &&
           message.find("[DRV_ERR]Failed to delete jfce, ret:") != std::string::npos;
}

std::string UrmaFailure480::GetName() const
{
    return "下层资源删除失败导致删除JFCE失败";
}

std::string UrmaFailure480::GetRootCauseDesc() const
{
    return "urma_delete_jfce清理JFCE时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure480::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure480::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure480::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfce，[DRV_ERR]Failed to delete jfce, ret:。";
}

std::string UrmaFailure480::GetId() const
{
    return "urma_480";
}
} // namespace diag

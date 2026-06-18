#include "urma_failure_360.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure360> g_urma("urma_360");

bool UrmaFailure360::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfce") != std::string::npos &&
           message.find("Failed to delete pjfce.") != std::string::npos;
}

std::string UrmaFailure360::GetName() const
{
    return "下层资源删除失败导致删除JFCE失败";
}

std::string UrmaFailure360::GetRootCauseDesc() const
{
    return "bondp_delete_jfce清理JFCE时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure360::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure360::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure360::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfce，Failed to delete pjfce.。";
}

std::string UrmaFailure360::GetId() const
{
    return "urma_360";
}
} // namespace diag

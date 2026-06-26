#include "urma_failure_516.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure516> g_urma("urma_516");

bool UrmaFailure516::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_vcontext") != std::string::npos &&
           message.find("Failed to urma_cmd_delete_context") != std::string::npos;
}

std::string UrmaFailure516::GetName() const
{
    return "下层资源删除失败导致删除vcontext失败";
}

std::string UrmaFailure516::GetRootCauseDesc() const
{
    return "bondp_delete_vcontext清理vcontext时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure516::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure516::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure516::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_vcontext，Failed to urma_cmd_delete_context。";
}

std::string UrmaFailure516::GetId() const
{
    return "urma_516";
}
} // namespace diag

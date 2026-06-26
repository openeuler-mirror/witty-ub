#include "urma_failure_030.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure030> g_urma("urma_030");

bool UrmaFailure030::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pcontext") != std::string::npos &&
           message.find("Failed to init port info list") != std::string::npos;
}

std::string UrmaFailure030::GetName() const
{
    return "创建pcontext执行失败导致创建pcontext失败";
}

std::string UrmaFailure030::GetRootCauseDesc() const
{
    return "bondp_create_pcontext执行创建pcontext时依赖的创建pcontext步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure030::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure030::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure030::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pcontext，Failed to init port info list。";
}

std::string UrmaFailure030::GetId() const
{
    return "urma_030";
}
} // namespace diag

#include "urma_failure_294.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure294> g_urma("urma_294");

bool UrmaFailure294::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_vjetty") != std::string::npos &&
           message.find("Failed to fill health check seg info for vjetty") != std::string::npos;
}

std::string UrmaFailure294::GetName() const
{
    return "创建vjetty执行失败导致创建vjetty失败";
}

std::string UrmaFailure294::GetRootCauseDesc() const
{
    return "bondp_create_vjetty执行创建vjetty时依赖的创建vjetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure294::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure294::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure294::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vjetty，Failed to fill health check seg info for vjetty。";
}

std::string UrmaFailure294::GetId() const
{
    return "urma_294";
}
} // namespace diag

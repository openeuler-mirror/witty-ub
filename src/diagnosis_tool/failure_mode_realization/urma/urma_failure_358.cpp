#include "urma_failure_358.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure358> g_urma("urma_358");

bool UrmaFailure358::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfce") != std::string::npos &&
           message.find("Failed to create pjfce.") != std::string::npos;
}

std::string UrmaFailure358::GetName() const
{
    return "下层资源创建失败导致创建JFCE失败";
}

std::string UrmaFailure358::GetRootCauseDesc() const
{
    return "bondp_create_jfce在创建JFCE过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure358::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure358::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure358::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfce，Failed to create pjfce.。";
}

std::string UrmaFailure358::GetId() const
{
    return "urma_358";
}
} // namespace diag

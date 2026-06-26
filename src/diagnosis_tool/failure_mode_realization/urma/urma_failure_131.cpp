#include "urma_failure_131.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure131> g_urma("urma_131");

bool UrmaFailure131::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_vjfs") != std::string::npos &&
           message.find("ubcore create jfs failed.") != std::string::npos;
}

std::string UrmaFailure131::GetName() const
{
    return "下层资源创建失败导致创建虚拟JFS失败";
}

std::string UrmaFailure131::GetRootCauseDesc() const
{
    return "bondp_create_vjfs在创建虚拟JFS过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure131::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure131::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure131::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vjfs，ubcore create jfs failed.。";
}

std::string UrmaFailure131::GetId() const
{
    return "urma_131";
}
} // namespace diag

#include "urma_failure_007.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure007> g_urma("urma_007");

bool UrmaFailure007::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_vjfr") != std::string::npos &&
           message.find("bondp init jfr fail:") != std::string::npos;
}

std::string UrmaFailure007::GetName() const
{
    return "创建虚拟JFR执行失败导致创建虚拟JFR失败";
}

std::string UrmaFailure007::GetRootCauseDesc() const
{
    return "bondp_create_vjfr执行创建虚拟JFR时依赖的创建虚拟JFR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure007::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure007::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure007::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vjfr，bondp init jfr fail:。";
}

std::string UrmaFailure007::GetId() const
{
    return "urma_007";
}
} // namespace diag

#include "urma_failure_669.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure669> g_urma("urma_669");

bool UrmaFailure669::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_modify_jfr") != std::string::npos &&
           message.find("modify pjfr fail, index:") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure669::GetName() const
{
    return "修改JFR执行失败导致修改JFR失败";
}

std::string UrmaFailure669::GetRootCauseDesc() const
{
    return "bondp_modify_jfr执行修改JFR时依赖的修改JFR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure669::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure669::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure669::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_modify_jfr，modify pjfr fail, index:，, ret:。";
}

std::string UrmaFailure669::GetId() const
{
    return "urma_669";
}
} // namespace diag
